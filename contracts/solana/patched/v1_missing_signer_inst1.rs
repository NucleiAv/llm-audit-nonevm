// V1: Missing signer check - Instance 1 (PATCHED)
// Fix: caller is now Signer<'info> and constrained to equal pool.authority,
// so only the current authority can reassign upgrade control.

use anchor_lang::prelude::*;

declare_id!("JET111111111111111111111111111111111111111111");

#[program]
pub mod jet_pool {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>, authority: Pubkey) -> Result<()> {
        let pool = &mut ctx.accounts.pool;
        pool.authority = authority;
        pool.bump = *ctx.bumps.get("pool").unwrap();
        Ok(())
    }

    pub fn set_upgrade_authority(
        ctx: Context<SetUpgradeAuthority>,
        new_authority: Pubkey,
    ) -> Result<()> {
        let pool = &mut ctx.accounts.pool;
        pool.authority = new_authority;
        Ok(())
    }

    pub fn deposit(ctx: Context<Deposit>, amount: u64) -> Result<()> {
        let pool = &mut ctx.accounts.pool;
        pool.total_deposits = pool.total_deposits.wrapping_add(amount);
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
pub struct SetUpgradeAuthority<'info> {
    #[account(
        mut,
        seeds = [b"pool"],
        bump = pool.bump,
        has_one = authority
    )]
    pub pool: Account<'info, Pool>,
    // FIX: Signer<'info> enforces that the transaction was signed by this key,
    // and has_one = authority ensures it equals pool.authority.
    pub authority: Signer<'info>,
}

#[derive(Accounts)]
pub struct Deposit<'info> {
    #[account(mut, seeds = [b"pool"], bump = pool.bump)]
    pub pool: Account<'info, Pool>,
    pub depositor: Signer<'info>,
}

#[account]
pub struct Pool {
    pub authority: Pubkey,
    pub total_deposits: u64,
    pub bump: u8,
}

impl Pool {
    pub const SIZE: usize = 32 + 8 + 1;
}
