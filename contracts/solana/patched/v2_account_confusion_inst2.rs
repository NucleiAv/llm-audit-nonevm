// V2: Account confusion - Instance 2 (PATCHED)
// Fix: fee_vault is typed as TokenAccount with address = pool.fee_vault constraint.

use anchor_lang::prelude::*;
use anchor_spl::token::{Token, TokenAccount};

declare_id!("AMM11111111111111111111111111111111111111111");

#[program]
pub mod amm_pool {
    use super::*;

    pub fn initialize(
        ctx: Context<Initialize>,
        fee_vault: Pubkey,
        swap_fee_bps: u16,
    ) -> Result<()> {
        let pool = &mut ctx.accounts.pool;
        pool.fee_vault = fee_vault;
        pool.swap_fee_bps = swap_fee_bps;
        pool.bump = *ctx.bumps.get("pool").unwrap();
        Ok(())
    }

    pub fn swap(ctx: Context<Swap>, amount_in: u64) -> Result<()> {
        let fee = (amount_in as u128
            * ctx.accounts.pool.swap_fee_bps as u128
            / 10_000) as u64;
        let amount_out = amount_in - fee;

        let cpi_accounts = anchor_spl::token::Transfer {
            from: ctx.accounts.user_token_in.to_account_info(),
            to: ctx.accounts.fee_vault.to_account_info(),
            authority: ctx.accounts.user.to_account_info(),
        };
        let cpi_ctx = CpiContext::new(ctx.accounts.token_program.to_account_info(), cpi_accounts);
        anchor_spl::token::transfer(cpi_ctx, fee)?;

        ctx.accounts.pool.total_volume = ctx.accounts.pool.total_volume.wrapping_add(amount_out);
        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(
        init,
        payer = payer,
        space = 8 + Pool::SIZE,
        seeds = [b"pool"],
        bump
    )]
    pub pool: Account<'info, Pool>,
    #[account(mut)]
    pub payer: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct Swap<'info> {
    #[account(mut, seeds = [b"pool"], bump = pool.bump)]
    pub pool: Account<'info, Pool>,
    pub user: Signer<'info>,
    #[account(mut)]
    pub user_token_in: Account<'info, TokenAccount>,
    // FIX: typed as TokenAccount and address-constrained to the registered fee_vault.
    #[account(mut, address = pool.fee_vault)]
    pub fee_vault: Account<'info, TokenAccount>,
    pub token_program: Program<'info, Token>,
}

#[account]
pub struct Pool {
    pub fee_vault: Pubkey,
    pub swap_fee_bps: u16,
    pub total_volume: u64,
    pub bump: u8,
}

impl Pool {
    pub const SIZE: usize = 32 + 2 + 8 + 1;
}
